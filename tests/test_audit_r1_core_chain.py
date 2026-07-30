"""全库三轮审查 · 第 1 轮（核心问答链路）修复项的护栏测试。

报告：docs/superpowers/specs/2026-07-30-audit-round1-core-chain.md

每个 class 对应报告里的一条 HIGH，注释写明「不修会怎样」，
以便日后有人回退实现时能从失败信息直接读出后果。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

DB = Path("db/wh40k.sqlite")
needs_db = pytest.mark.skipif(not DB.exists(), reason="需要 db/wh40k.sqlite")

INTERCESSOR = "000001157"   # 5/10 档，射击武器池多把（需显式 loadout）
TERMAGANTS = "000000468"    # 守方


class _Choice:
    """openai 形状的 choice；finish_reason 可选（老 SDK / 假客户端可能没有）。"""

    def __init__(self, content, finish_reason=None):
        class _Msg:
            pass
        self.message = _Msg()
        self.message.content = content
        if finish_reason is not None:
            self.finish_reason = finish_reason


class _ScriptedClient:
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

        class _Completions:
            def create(_self, **kwargs):
                self.calls += 1
                return type("_Resp", (), {"choices": [self._script.pop(0)]})

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


class TestH2TruncatedRefineMustNotBeCachedAsComplete:
    """H2：finish_reason=length 的截断产物曾以 fallback=False / verify_ok=True 落盘。

    截断内容非空 ⇒ 旧代码直接 return ⇒ is_cached 永远命中、永不重跑，
    该页正文从向量库整体消失，且 verify_numbers（只查「多出来的数字」的单向校验器）
    对「少了一整页」在数学上不可能有反应。
    """

    def test_truncated_response_is_retried_then_raises(self, monkeypatch):
        import llm_refine

        monkeypatch.setattr(llm_refine.time, "sleep", lambda s: None)
        client = _ScriptedClient([
            _Choice("# ROBOUTE GUILLIMAN\n\n**M** 6", finish_reason="length"),
            _Choice("# ROBOUTE GUILLIMAN\n\n**M** 6", finish_reason="length"),
            _Choice("# ROBOUTE GUILLIMAN\n\n**M** 6", finish_reason="length"),
        ])
        with pytest.raises(RuntimeError) as ei:
            llm_refine.refine_page(client, "源文本" * 500, "")
        assert "截断" in str(ei.value)
        assert client.calls == llm_refine.MAX_RETRIES, "截断必须走既有重试通道"

    def test_truncation_recovers_when_retry_completes(self, monkeypatch):
        import llm_refine

        monkeypatch.setattr(llm_refine.time, "sleep", lambda s: None)
        client = _ScriptedClient([
            _Choice("半页就没了", finish_reason="length"),
            _Choice("## 完整页", finish_reason="stop"),
        ])
        assert llm_refine.refine_page(client, "源文本", "") == "## 完整页"

    def test_anthropic_style_max_tokens_also_counts_as_truncation(self, monkeypatch):
        import llm_refine

        monkeypatch.setattr(llm_refine.time, "sleep", lambda s: None)
        client = _ScriptedClient([_Choice("半页", finish_reason="max_tokens"),
                                  _Choice("## 完整页", finish_reason="stop")])
        assert llm_refine.refine_page(client, "源文本", "") == "## 完整页"

    def test_missing_finish_reason_is_not_treated_as_truncation(self):
        """老 SDK / 假客户端没有该字段时按现状放行——只在确知截断时失败，不猜。"""
        import llm_refine

        client = _ScriptedClient([_Choice("## 正常页")])
        assert llm_refine.refine_page(client, "源文本", "") == "## 正常页"
        assert client.calls == 1

    def test_truncated_page_falls_back_and_is_not_cached(self, monkeypatch, tmp_path):
        """端到端：截断页最终以 fallback=True 落盘 ⇒ is_cached 判 False ⇒ 下次会重跑。"""
        import llm_refine

        def _always_truncated(client, text, prev_tail, sp=None):
            raise RuntimeError("LLM 处理失败（重试3次）: LLM 输出被 max_tokens 截断")

        monkeypatch.setattr(llm_refine, "refine_page", _always_truncated)
        monkeypatch.setattr(llm_refine, "extract_pages", lambda p: [
            {"page": 1, "text": "源" * 400, "sha256": "abc"}])

        summary = llm_refine.process_book(None, Path("Book.pdf"), tmp_path, workers=1)
        assert summary["failed"] == 1 and summary["done"] == 0
        book_dir = tmp_path / "Book"
        _, meta_path = llm_refine.page_paths(book_dir, 1)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert meta["fallback"] is True
        assert llm_refine.is_cached(book_dir, 1, "abc", meta["prompt_version"]) is False


class TestH3ZeroCountLoadoutMustFailLoudly:
    """H3：显式 loadout 的件数 ≤0 曾经装配"成功"，端出全 0 的期望伤害报告。

    引擎层（sequence.py:225）对 count<=0 是对的——诚实地不开火。
    正因为它对，错误才以最危险的形态冒出来：工具边界把这个诚实的 0
    包装成 ok=True / expected_damage=0.0 / warning=None 的成功报告。
    """

    @needs_db
    def test_zero_count_is_an_assembly_error_not_a_silent_zero(self):
        from engines.simulator.assembly import assemble_attacker

        res = assemble_attacker(DB, INTERCESSOR, models=5, phase="shooting",
                                loadout=[("Bolt rifle", 0)])
        assert res is not None
        assert res.ambiguous is True, "件数 0 必须走显式失败通道"
        assert res.attacker is None, "不许装配出一个 0 件的攻击者"
        assert any("≤ 0" in e for e in res.errors), res.errors

    @needs_db
    def test_negative_count_is_rejected_too(self):
        from engines.simulator.assembly import assemble_attacker

        res = assemble_attacker(DB, INTERCESSOR, models=5, phase="shooting",
                                loadout=[("Bolt rifle", -5)])
        assert res.ambiguous is True and res.attacker is None
        assert any("≤ 0" in e for e in res.errors), res.errors

    @needs_db
    def test_zero_count_entry_poisons_the_whole_loadout(self):
        """混装（一把正常 + 一把 0 件）同样显式失败——不许静默丢掉那把 0 件的。"""
        from engines.simulator.assembly import assemble_attacker

        res = assemble_attacker(DB, INTERCESSOR, models=5, phase="shooting",
                                loadout=[("Bolt rifle", 5), ("Bolt pistol", 0)])
        assert res.ambiguous is True and res.attacker is None
        assert any("≤ 0" in e for e in res.errors), res.errors

    @needs_db
    def test_positive_count_still_assembles(self):
        """回归护栏：正常件数一个字节不变（防止修法过度收紧）。"""
        from engines.simulator.assembly import assemble_attacker

        res = assemble_attacker(DB, INTERCESSOR, models=5, phase="shooting",
                                loadout=[("Bolt rifle", 5)])
        assert res.ambiguous is False and res.errors == []
        assert res.attacker is not None
        assert [(w.name_en, w.count) for w in res.attacker.loadout] == [("Bolt rifle", 5)]

    @needs_db
    def test_tool_boundary_returns_loadout_required_not_a_zero_damage_report(self):
        """工具边界：模型看到的必须是显式失败，不是 ok=True 的全 0 报告。"""
        from agent.tools import simulate_combat_resolved

        out = simulate_combat_resolved(
            {"canonical_id": INTERCESSOR, "name_en": "Intercessor Squad"},
            {"canonical_id": TERMAGANTS, "name_en": "Termagants"},
            {"phase": "shooting", "n": 200, "seed": 7,
             "loadout": [["Bolt rifle", 0]]},
            db_path=DB)
        assert out["ok"] is False, (
            "假成功：ok=True + expected_damage 0.0 会被模型答成「期望伤害为 0」")
        assert out.get("reason") == "loadout_required"
        assert any("≤ 0" in e for e in out.get("errors", [])), out.get("errors")
